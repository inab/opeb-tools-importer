#!/usr/bin/env python3

import argparse
import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

from utils import get_url, connect_db, update_entry, add_metadata_to_entry


def get_source(id_: str):
    """
    Extract source from an OpenEBench tool @id.

    Example:
    https://openebench.bsc.es/monitor/tool/biotools:panalyzer/app/www.ehubio.es
    -> biotools
    """
    parts = id_.split("/")
    if len(parts) <= 5:
        return None

    string = parts[5]
    source = string.split(":")[0]
    return source


def get_bioconda_biotools_galaxy_tools(tool: dict):
    """
    Detect whether the tool comes from biotools, bioconda, or galaxy
    based on the @id structure.

    Returns:
        - modified tool if recognized
        - None if the structure does not match
    """
    tool_id = tool.get("@id", "")

    if tool_id.count("/") > 5:
        source = get_source(tool_id)

        if source == "biotools":
            tool["@data_source"] = "biotools"
        elif source == "bioconda":
            tool["@data_source"] = "bioconda"
        elif source == "galaxy":
            tool["@data_source"] = "galaxy"
        else:
            return None

        tool["@source_url"] = tool_id
        return tool

    return None


def append_line(path: Path, text: str) -> None:
    """
    Append one line to a text file.
    """
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def build_identifier(tool: dict) -> str | None:
    """
    Build internal identifier for Mongo entry.

    Returns None if required fields are missing.
    """
    source = tool.get("@data_source")
    name = tool.get("@label")
    type_ = tool.get("@type")
    version = tool.get("@version")

    if not source or not name or not type_:
        return None

    if not version:
        version = "unknown"

    return f"{source}/{name}/{type_}/{version}"


def is_deprecated(tool: dict) -> bool:
    """
    Return True when the tool is explicitly marked as deprecated.
    """
    return tool.get("deprecated") is True


def get_exact_name(tool: dict) -> str | None:
    """
    Return the exact tool name used for duplicate/deprecation workaround.

    We use @label because that is the name field used to build the internal ID.
    """
    return tool.get("@label")


def collect_non_deprecated_biotools_names(tools: list[dict]) -> set[str]:
    """
    First pass:
    collect exact names (@label) of valid biotools records that are not deprecated.
    """
    names = set()

    for raw_tool in tools:
        tool = get_bioconda_biotools_galaxy_tools(raw_tool)
        if not tool:
            continue

        if tool.get("@data_source") != "biotools":
            continue

        if is_deprecated(tool):
            continue

        name = get_exact_name(tool)
        if name:
            names.add(name)

    return names


def import_data():
    try:
        parser = argparse.ArgumentParser(
            description="Importer of OpenEBench tools from OpenEBench Tool API"
        )
        parser.add_argument(
            "--loglevel",
            "-l",
            help="Set the logging level",
            default="INFO",
        )
        parser.add_argument(
            "--inspection-dir",
            default="inspection_openebench_import",
            help="Directory where processed IDs will be written.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without saving anything to MongoDB.",
        )

        args = parser.parse_args()
        numeric_level = getattr(logging, args.loglevel.upper(), logging.INFO)

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )

        logging.info("state_importation - 1")
        if args.dry_run:
            logging.info("Running in DRY-RUN mode. No data will be written to MongoDB.")

        inspection_dir = Path(args.inspection_dir)
        inspection_dir.mkdir(parents=True, exist_ok=True)

        all_ids_file = inspection_dir / "all_ids.txt"
        ids_over_5_file = inspection_dir / "ids_count_slash_over_5.txt"
        ids_under_or_equal_5_file = inspection_dir / "ids_count_slash_5_or_less.txt"
        biotools_ids_file = inspection_dir / "biotools_ids_seen.txt"
        processed_biotools_ids_file = inspection_dir / "processed_biotools_ids.txt"
        skipped_non_biotools_ids_file = inspection_dir / "skipped_non_biotools_ids.txt"
        skipped_missing_fields_file = inspection_dir / "skipped_missing_required_fields.txt"
        skipped_deprecated_file = inspection_dir / "skipped_deprecated.txt"
        saved_deprecated_file = inspection_dir / "saved_deprecated_due_to_missing_active_duplicate.txt"
        failed_ids_file = inspection_dir / "failed_ids.txt"
        dry_run_candidates_file = inspection_dir / "dry_run_candidates.txt"

        alambique = None
        if not args.dry_run:
            logging.info("Connecting to database")
            alambique = connect_db("alambique")
        else:
            logging.info("Skipping MongoDB connection because --dry-run is enabled")

        logging.info("Downloading OPEB tools")
        URL_OPEB_TOOLS = os.getenv(
            "URL_OPEB_TOOLS",
            "https://openebench.bsc.es/monitor/tool"
        )
        logging.info(f"OpenEBench tools URL: {URL_OPEB_TOOLS}")

        tools = get_url(URL_OPEB_TOOLS)

        if not tools:
            logging.error("error - crucial_object_empty")
            logging.error("No content to process. Exiting...")
            logging.info("state_importation - 2")
            sys.exit(1)

        logging.info("Tools obtained")
        logging.info(f"Processing {len(tools)} tools ...")

        # ------------------------------------------------------------------
        # First pass: collect exact names of non-deprecated biotools entries
        # ------------------------------------------------------------------
        active_biotools_names = collect_non_deprecated_biotools_names(tools)
        logging.info(
            f"Collected {len(active_biotools_names)} exact names from non-deprecated biotools records"
        )

        n_seen = 0
        n_structure_ok = 0
        n_biotools_seen = 0
        n_processed = 0
        n_skipped_non_biotools = 0
        n_skipped_missing_fields = 0
        n_skipped_deprecated = 0
        n_saved_deprecated = 0
        n_failed = 0
        n_dry_run_candidates = 0

        for raw_tool in tools:
            tool_id = raw_tool.get("@id", "<missing @id>")
            n_seen += 1

            append_line(all_ids_file, tool_id)

            try:
                if tool_id.count("/") > 5:
                    append_line(ids_over_5_file, tool_id)
                    n_structure_ok += 1
                else:
                    append_line(ids_under_or_equal_5_file, tool_id)

                tool = get_bioconda_biotools_galaxy_tools(raw_tool)

                if not tool:
                    logging.debug(f"Skipping by structure/source: {tool_id}")
                    continue

                if tool.get("@data_source") == "biotools":
                    append_line(biotools_ids_file, tool_id)
                    n_biotools_seen += 1

                if tool.get("@data_source") != "biotools":
                    append_line(
                        skipped_non_biotools_ids_file,
                        f"{tool_id}\tdata_source={tool.get('@data_source')}"
                    )
                    n_skipped_non_biotools += 1
                    continue

                # ----------------------------------------------------------
                # Deprecated workaround:
                # - if there is an active record with same exact name, skip
                # - otherwise keep the deprecated record
                # ----------------------------------------------------------
                if is_deprecated(tool):
                    exact_name = get_exact_name(tool)

                    if exact_name in active_biotools_names:
                        append_line(
                            skipped_deprecated_file,
                            (
                                f"{tool_id}\t"
                                f"label={tool.get('@label')}\t"
                                f"type={tool.get('@type')}\t"
                                f"version={tool.get('@version')}\t"
                                f"deprecated={tool.get('deprecated')}\t"
                                f"reason=active_record_with_same_exact_name_exists"
                            )
                        )
                        n_skipped_deprecated += 1
                        logging.info(
                            f"Skipping deprecated tool because active duplicate exists: {tool_id}"
                        )
                        continue
                    else:
                        append_line(
                            saved_deprecated_file,
                            (
                                f"{tool_id}\t"
                                f"label={tool.get('@label')}\t"
                                f"type={tool.get('@type')}\t"
                                f"version={tool.get('@version')}\t"
                                f"deprecated={tool.get('deprecated')}\t"
                                f"reason=no_active_record_with_same_exact_name"
                            )
                        )
                        n_saved_deprecated += 1
                        logging.info(
                            f"Keeping deprecated tool because no active duplicate exists: {tool_id}"
                        )

                identifier = build_identifier(tool)
                if not identifier:
                    append_line(
                        skipped_missing_fields_file,
                        (
                            f"{tool_id}\t"
                            f"label={tool.get('@label')}\t"
                            f"type={tool.get('@type')}\t"
                            f"version={tool.get('@version')}\t"
                            f"data_source={tool.get('@data_source')}"
                        )
                    )
                    n_skipped_missing_fields += 1
                    logging.warning(
                        f"Skipping tool with missing required fields: {tool_id}"
                    )
                    continue

                entry = {
                    "data": tool,
                    "_id": identifier,
                    "@data_source": tool["@data_source"],
                }

                if args.dry_run:
                    append_line(
                        dry_run_candidates_file,
                        f"{tool_id}\t{identifier}"
                    )
                    append_line(
                        processed_biotools_ids_file,
                        f"{tool_id}\t{identifier}\tDRY_RUN"
                    )
                    n_dry_run_candidates += 1
                    n_processed += 1
                    #logging.info(f"[DRY-RUN] Would process: {identifier}")
                    continue

                #logging.info(f"Creating metadata for: {identifier}")
                document_w_metadata = add_metadata_to_entry(identifier, entry, alambique)

                #logging.info(f"Updating document: {identifier}")
                update_entry(document_w_metadata, alambique)

                append_line(processed_biotools_ids_file, f"{tool_id}\t{identifier}")
                n_processed += 1

            except Exception as e:
                n_failed += 1
                append_line(failed_ids_file, f"{tool_id}\t{type(e).__name__}\t{e}")
                logging.exception(f"Exception while processing tool: {tool_id}")
                continue

        logging.info(f"Seen tools: {n_seen}")
        logging.info(f"Tools with @id count('/') > 5: {n_structure_ok}")
        logging.info(f"biotools tools seen: {n_biotools_seen}")
        logging.info(f"Processed biotools tools: {n_processed}")
        logging.info(f"Skipped non-biotools tools: {n_skipped_non_biotools}")
        logging.info(f"Skipped deprecated tools: {n_skipped_deprecated}")
        logging.info(f"Saved deprecated tools with no active duplicate: {n_saved_deprecated}")
        logging.info(f"Skipped due to missing required fields: {n_skipped_missing_fields}")
        logging.info(f"Failed tools: {n_failed}")
        if args.dry_run:
            logging.info(f"Dry-run candidate writes: {n_dry_run_candidates}")
        logging.info("state_importation - 0")

    except Exception as e:
        logging.exception("Exception occurred")
        logging.error(f"error - {type(e).__name__} - {e}")
        logging.info("state_importation - 2")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()
    import_data()