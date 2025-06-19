# list tasks
default:
    @just -l

# render the website
render-site:
    quarto render

# upload public assets to separate web repo
upload-web-assets:
    @echo '{{ BOLD + CYAN }}pushing static images{{ NORMAL }}'
    dvc push --no-run-cache -r public -R images
    @echo '{{ BOLD + CYAN }}pushing page outputs{{ NORMAL }}'
    dvc push --no-run-cache -r public dvc.yaml
