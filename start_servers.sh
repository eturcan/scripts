MORPH_PATH=scripts_sum/scripts-morph-v4.4.jar 
MORPH_PORT=9099
DOC_PORT=9100
QUERY_PORT=9101
ANNOTATION_PORT=9102
NIST_DATA=/storage/data/NIST-data
ANNOTATION_CONFIG=configs/annotationserver.json
MODEL_DIR=/storage/proj/kedz/summarizer_checkout/op1/models
source activate matsum

java -jar $MORPH_PATH $MORPH_PORT EN &
doc_server $DOC_PORT $NIST_DATA configs/docserver_config.json &
query_server $QUERY_PORT $MORPH_PORT $NIST_DATA &
annotation_server $ANNOTATION_PORT $QUERY_PORT $DOC_PORT $MODEL_DIR $ANNOTATION_CONFIG &

trap 'kill $(jobs -p)' EXIT
wait
