update-pipeline:
    ./scripts/render-pipeline.ts

upload-web-assets:
    dvc push -r web-assets --no-run-cache dvc.yaml

render:
    quarto render

deploy: render
    netlify deploy -d _site --prod
