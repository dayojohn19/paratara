import minify_html
def mini(path):
    print('starting minify')
    if path.lower().endswith(".css"): 
        compress_css(path)
        return

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(f"{path}_before_minify", "w", encoding="utf-8") as f:
        f.write(html)    
    minified = minify_html.minify(
        html,
        minify_css=True,
        minify_js=True,
    )
    print('done minified')
    with open(path, "w", encoding="utf-8") as f:
        f.write(minified)    


def compress_css(path):
    #  MINIFI CSS        # 
    from csscompressor import compress
    print('compressing css')
    with open(path, "r", encoding="utf-8") as f:
        css = f.read()
    with open(f"{path}_before_minify", "w", encoding="utf-8") as f:
        f.write(css)    
    print('compressing css')
    minified = compress(css)
    with open("style.min.css", "w", encoding="utf-8") as f:
        f.write(minified)
