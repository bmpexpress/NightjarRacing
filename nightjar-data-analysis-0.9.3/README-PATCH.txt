Nightjar 0.9.3 login and colour-bar patch
1. Overwrite src/main/resources/static/styles.css.
2. Add src/main/resources/static/plot-colourbars.js.
3. In the existing src/main/resources/static/index.html, immediately after the existing /app.js script tag, add:
   <script src="/plot-colourbars.js"></script>
