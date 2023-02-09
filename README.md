# OPEB Tools importer 

Imports those entries in OPEB that were originally retrieved from bioconda and biotools.

## Set-up and Usage

### Option 1 (RECOMENDED) - Docker container 
The easiest way to run this importer is by using a docker image.
1. Pull the image 

    ```sh
    docker login registry.gitlab.bsc.es
    docker pull registry.gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer
    ```

2. Run the container. 
If the ENV variables are stored in an `.env` file: 
    ```sh
    docker run --name [container-name] --env-file .env registry.gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer
    ```

> :bulb: **Using `linux/amd64` architecture to run (and build) the container** 
>
>```sh
>export DOCKER_DEFAULT_PLATFORM=linux/amd64 
>```
> Necessary to run this container in a MacBook with M1 chip.


> :bulb: **Connecting to services in host** 
>
> Use `host.docker.internal` instead of `localhost` in the container to reach local services. For instance, to connect to a local MongoDB, use the string `host.docker.internal:27017`. 


### Option 2 - Native 

1. Clone this repository.

2. Install Python packages listed in `requirements.txt`.

    ```sh
    pip install -r requirements.txt
    ```

3. Execute the importer

    ```sh
    python3 main.py -l=info
    ``` 
    `-l/--loglevel` argument can be `debug`, `info`, `warning`, `error` or `critical`. It is optional and defaults to `info`.

> This program has been successfully executed using Python 3.8 and 3.9.


## Configuration

### Environment variables 

| Name             | Description | Default | Notes |
|------------------|-------------|---------|-------|
| STORAGE_MODE     |  Specifies whether the output will be stored in filesystem (`filesystem`) or pushed to a database (`db`) |  `db` |            |
| HOST       |  Host of database where output will be pushed |   `localhost`        |  Only used when STORAGE_MODE is `db`      |
| PORT       |  Port of database where output will be pushed |   `27017`            |  Only used when STORAGE_MODE is `db`      |
| DB         |  Name of database where output will be pushed |   `observatory`      |  Only used when STORAGE_MODE is `db`      |
| ALAMBIQUE |  Name of database where output will be pushed  |   `alambique`        |  Only used when STORAGE_MODE is `db`      |
| OUTPUT_PATH      |  Path to output file                    | `./data/bioconda.json` |  Only used when STORAGE_MODE is `filesystem` | 
| URL_OPEB_TOOLS | URL to OpenEBench Tools API | `https://openebench.bsc.es/monitor/tool` | |

