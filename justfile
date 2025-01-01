# list recipes
list:
    just -l

# render the website
render:
    quarto render --to html

# push web assets to the cloud
upload-web-assets:
    dvc push --no-run-cache -r public dvc.yaml
    dvc push --no-run-cache -r public -R images

# fetch web assets from the cloud
fetch-web-assets:
    dvc pull --no-run-cache -r public dvc.yaml
    dvc pull --no-run-cache -r public -R images

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
