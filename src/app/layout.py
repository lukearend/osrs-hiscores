import frontmatter, lookup, controls, scatterplot, tables, boxplot

def root():
    return container([
        row(
            col([
                frontmatter.title(),
                frontmatter.blurb()
            ])
        ),
        row(
            col([
                lookup.lookup_box(),
                lookup.player_bubbles(),
                lookup.result_text()
            ])
        ),
        row(
            col([
                controls.split_dropdown(),
                controls.point_size_dropdown()
            ])
        ),
        row(
            col(
                scatterplot.figure(),
            )
        ),
        row(
            col([
                tables.player_table(),
                tables.cluster_table()
            ])
        ),
        row(
            col(
                boxplot.figure()
            )
        )
    ])

def container(content):
    pass

def row(content):
    pass

def col(content):
    pass
