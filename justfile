# list recipes
list:
    just -l

# render the website
render:
    quarto render

# update the DVC pipeline
update-pipeline:
    ./scripts/render-pipeline.ts

# push web assets to the cloud
upload-web-assets:
    dvc push -r web-assets --no-run-cache dvc.yaml
