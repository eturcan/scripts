# scripts
SCRIPTS summarization system for IARPA MATERIAL project.

This is the code for running the summarization docker. The starting scripts can be found in **docker/bin**, which will be introduced below.

## Running Summarizer for Evaluation

To run the summarizer for evaluation, we expect the following input from CLIR experiment folder (located at **/experiment**)

- A single json config specifying the following keys:

    - data_collection.data_store_structure: **str** specifying the data structure file
    - data_collection.collections: **List[str]** specifying the list of collection paths
    - query_processor.query_list_path: **str** path to the query analyzer directory. We use this to prepare the list of queries we summarize
    -query_processor.psq_keys: **List[str]** list of psq keys we use to generate the psq annotators

- UMD-CLIR-workECDir : A directory with the following files queryxxx.tsv, where xxx is a number of the query id. This file should have three columns, the document id, the relevance judgment (Y if relevante else N), and relevance score

- UMD-CLIR-workECDir-f1 : Optional directory for using retranslation. Should be only relevant for kk and ka.

The entrypoint for the script is **server_full**, which starts the server, summarize the queries, retranslate if necssary, and then package the files for submission. This script takes in the following arguments:

- run_name: The name of the package run 
- work_dir: The output directory. Relevant for retranslation that we need to run docker within docker
- num_procs: The number of processors to run.
- gpu_id: The gpu id to run translation docker or ape docker. Relevant only for retranslation

An example run is the following:

```
PIPELINE_DIR=/storage/proj/dw2735/experiments/docker_test/ps/text
OUTPUT_DIR=/storage/proj/dw2735/summarizer_output/docker_test/ps/text

CLIR=$PIPELINE_DIR/UMD-CLIR-workECDir
NIST_VOL="-v /storage/data/NIST-data:/NIST-data"
EXPERIMENT_VOL="-v $PIPELINE_DIR:/experiment"
CLIR_VOL="-v $CLIR:/clir"
OUTPUT_VOL="-v $OUTPUT_DIR:/outputs"

VERBOSE="-e VERBOSE=true"
run_name="CUSUM"
work_dir=$OUTPUT_DIR
num_procs=12
gpu_id=0

docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
        $NIST_VOL $OUTPUT_VOL $CLIR_VOL $EXPERIMENT_VOL -it --user "$(id -u):$(id -g)" --group-add $(stat -c '%g' /var/run/docker.sock) --rm $VERBOSE \
        --name sumtest --ipc=host summarizer:v3.0 $run_name $work_dir $num_procs $gpu_id
```

Of course, you can always run each component separately, which you can read through **server_full** to understand.

## Demo

The entrypoint for demo is **server_demo** for the server and **summarize_queries_demo** to run the client