import os
import torch

edinmt="scriptsmt-systems-v20"
umdnmt="umd-nmt-v5.3"
umdsmt="umd-smt-v3.2"

#asr="material-asr-ka-uedin-v1.0-cued-v2.1"
asr="material-asr-fa-combination-v2.0"

path="/storage/data/NIST-data/3S/IARPA_MATERIAL_OP2-3S/"
out_dir="/storage/proj/dw2735/summarizer_docker/docker/models/emb/roberta_embs/fa/EVAL"

#collections = ["ANALYSIS","DEV"]
collections= ["EVAL"]

keys = ["corpus_embeddings","corpus_sentences"]

# mt embeddings

for mt_key, mt_path in [("edi-nmt",edinmt),("umd-nmt",umdnmt),("umd-smt",umdsmt)]:
    #for mt_key, mt_path in enumerate([]):
    comb_dict = {k:dict() for k in keys}
    for collection in collections:
        # text
        text_path = os.path.join(path,collection,"text","embedding_store","sbert.net_models_roberta-large-nli-stsb-mean-tokens","{}_docs_sentence_embeddings.torch".format(mt_path))
        print(text_path)
        text_emb = torch.load(text_path)
        for key in keys:
            comb_dict[key].update(text_emb[key])
        # audio
        audio_path = os.path.join(path,collection,"audio","embedding_store","sbert.net_models_roberta-large-nli-stsb-mean-tokens","{}_{}_docs_sentence_embeddings.torch".format(mt_path, asr))
        print(audio_path)
        audio_emb = torch.load(audio_path)
        for key in keys:
            comb_dict[key].update(audio_emb[key])

    torch.save(comb_dict, os.path.join(out_dir,"{}.torch".format(mt_key)))

# query embeddings

#audio_path="/storage/proj/dw2735/summarizer_docker/docker/models/emb/roberta_embs/ka/QUERY1/QUERY1_audio.torch"
#text_path="/storage/proj/dw2735/summarizer_docker/docker/models/emb/roberta_embs/ka/QUERY1/QUERY1_text.torch"

#comb_dict = torch.load(audio_path)
#comb_dict.update(torch.load(text_path))
#torch.save(comb_dict, os.path.join(out_dir,"query.torch"))
