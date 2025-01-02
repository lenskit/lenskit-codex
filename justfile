DENO_RUN := "deno run --allow-read=. --allow-write=. --allow-net=deno.land --no-lock"

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
    {{DENO_RUN}} ./scripts/copy-docs.ts

# update the DVC pipeline
render-pipeline:
    #!/usr/bin/env zsh
    set -e
    {{DENO_RUN}} ./scripts/render-pipeline.ts
    pre-commit run --files **/dvc.yaml || true

# update the gitignore files
update-gitignore: render-pipeline
    {{DENO_RUN}} ./scripts/render-gitignore.ts

# update the whole project layout
rerender: update-documents render-pipeline update-gitignore
