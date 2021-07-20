from setuptools import setup

setup(
    name='scripts_sum',
    version='0.1',
    packages=['scripts_sum', 'sumquery', 'sumdoc', 'sumannotate', 
              'summarkup', 'sumpsq'],
    #py_modules=["package_summaries", "ds2config", "normalize_embeddings",
    #            "make_source_evidence"],
    py_modules=["package_summaries","ds2config"],
   # license='Creative Commons Attribution-Noncommercial-Share Alike license',
   # long_description=open('README.txt').read(),
    install_requires=["nltk", "numpy", "colorama", "sklearn", "jsonschema",
                      "imgkit", "torch", "mosestokenizer","sentencepiece"],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "sumpsq=sumpsq.server:sumpsq_server",
            "get_psq=sumpsq.client:get_psq",
            "annotation_server=sumannotate.server:main",
            "annotate_material=sumannotate.client:annotate_material",
            "reload_annotators=sumannotate.client:reload_annotators",
            "reload_config=sumannotate.client:reload_config",
            "doc_server=sumdoc.server:main",
            "query_server=sumquery.server:main",
            "list_queries=sumquery.client:list_queries",
            "list_relevant=sumquery.client:list_relevant",
            "is_relevant=sumquery.client:is_relevant",
            "num_components=sumquery.client:num_components",
            "is_lexical=sumquery.client:is_lexical",
            "is_simple=sumquery.client:is_simple",
            "is_morph=sumquery.client:is_morph",
            "is_conceptual=sumquery.client:is_conceptual",
            "is_example_of=sumquery.client:is_example_of",
            "doc_client=sumdoc.client:main",
            "generate_markup=summarkup.cli:generate_markup",
            "generate_image=summarkup.cli:generate_image",
            "package_summaries=package_summaries:main",
            "print_markup=scripts_sum.print_markup:main",
            "ds2config=ds2config:main",
        ],
    },
    package_data={
        # And include any *.dat files found in the 'data' subdirectory
        # of the 'mypkg' package, also:
            'scripts_sum': [
                'data/summarySchema_v1.3.1.json',
                'data/summarySchema_v1.3.2.json',
            ]

    }

)
