from websocket import create_connection
import json
import argparse


def main(args):
    ws = create_connection("ws://localhost:9000/")

    for file in os.listdir(args.input_dir):
        with open(os.path.join(args.input_dir, file)) as translation_config:
            input_dict = json.load(translation_config)
        ws.send(json.dumps(input_dict))
        result = ws.recv()
        if result is not None:
            try:
                output_dict = json.loads(result)
                with open(os.path.join(args.output_dir, file),"w") as out_file:
                    json.dump(output_dict)
            except:
                print("Error encountered for file {}".format(file))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str)
    parser.add_argument("--output_dir", type=str)

    args = parser.parse_args()
    main(args)
