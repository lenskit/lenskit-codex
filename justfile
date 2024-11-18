# list recipes
list:
    just -l

# render the website
render:
    quarto render --to html

# push web assets to the cloud
upload-web-assets:
    dvc push --no-run-cache -r assets-publish dvc.yaml

# fetch web assets from the cloud
fetch-web-assets:
    dvc pull --no-run-cache -r assets dvc.yaml

# update the copied documents
update-documents:
    ./scripts/copy-docs.ts

# update the DVC pipeline
update-pipeline:
    #!/usr/bin/env zsh
    set -e
    ./scripts/render-pipeline.ts
    pre-commit run --files **/dvc.yaml || true

# update the whole project layout
update-layout: update-documents update-pipeline

# update the Conda lockfile
update-deps:
    conda lock -f environment.yml -f lenskit-environment.yml

# create a Conda environment
create-env name="lk-codex":
    conda lock install -n {{name}}
