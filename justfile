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

# fetch public web assets
fetch-web-assets source="public":
    @echo '{{ BOLD + CYAN }}pulling page outputs{{ NORMAL }}'
    dvc pull --no-run-cache -r {{source}} dvc.yaml
    @echo '{{ BOLD + CYAN }}pulling static images{{ NORMAL }}'
    dvc pull --no-run-cache -r {{source}} -R images
