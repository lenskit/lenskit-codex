# list recipes
list:
    just -l

# render the website
render:
    quarto render

# push web assets to the cloud
upload-web-assets:
    dvc push -r web-assets --no-run-cache dvc.yaml

# update the DVC pipeline
update-pipeline:
    ./scripts/render-pipeline.ts

# update the Conda lockfile
update-deps:
    conda lock -f environment.yml -f lenskit-environment.yml

# create a Conda environment
create-env name="lk-codex"
    conda lock install -n {{name}}
