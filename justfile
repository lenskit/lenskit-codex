# list tasks
default:
    @just -l

# render the website
render-site:
    quarto render

# upload public assets to separate web repo
upload-web-assets:
    @echo '{{ BOLD + CYAN }}pushing static images{{ NORMAL }}'
    dvc push -j4 --no-run-cache -r public -R images
    @echo '{{ BOLD + CYAN }}pushing page outputs{{ NORMAL }}'
    dvc push -j4 --no-run-cache -r public dvc.yaml

# fetch public web assets
fetch-web-assets remote="public":
    @echo '{{ BOLD + CYAN }}pulling page outputs{{ NORMAL }}'
    dvc pull -j4 --no-run-cache -r {{remote}} dvc.yaml
    @echo '{{ BOLD + CYAN }}pulling static images{{ NORMAL }}'
    dvc pull -j4 --no-run-cache -r {{remote}} -R images
