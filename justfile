update-pipeline:
    ./render-pipeline.ts

render:
    quarto render

deploy: render
    netlify deploy -d _site --prod
