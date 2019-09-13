from setuptools import setup

setup(
    name='scripts_sum',
    version='0.1',
    packages=['scripts_sum', 'sumquery', 'sumdoc', 'sumannotate', 
              'summarkup'],
    py_modules=["package_summaries"],
   # license='Creative Commons Attribution-Noncommercial-Share Alike license',
   # long_description=open('README.txt').read(),
    install_requires=["nltk", "numpy", "colorama", "sklearn", "jsonschema",
                      "imgkit"],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "annotation_server=sumannotate.server:main",
            "annotate_material=sumannotate.client:annotate_material",
            "reload_annotators=sumannotate.client:reload_annotators",
            "reload_config=sumannotate.client:reload_config",
            "doc_server=sumdoc.server:main",
            "query_server=sumquery.server:main",
            "list_queries=sumquery.client:list_queries",
            "list_relevant=sumquery.client:list_relevant",
            "num_components=sumquery.client:num_components",
            "doc_client=sumdoc.client:main",
            "generate_markup=summarkup.cli:generate_markup",
            "generate_image=summarkup.cli:generate_image",
            "package_summaries=package_summaries:main",
        ],
    }
)
