# list tasks
default:
    @just -l

# render the website
render-site:
    quarto render

# upload public assets to separate web repo
upload-web-assets:
    @echo "pushing static images"
    dvc push --no-run-cache -r public -R images
    @echo "pushing page outputs"
    dvc push --no-run-cache -r public dvc.yaml
