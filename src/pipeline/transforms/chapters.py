
def build_page_map(capitoli):
    page_map = {}
    for cap_name, cap_data in capitoli.items():
        for sub_name, sub_range in cap_data["sottocapitoli"].items():
            sub_start, sub_end = sub_range
            for pg in range(sub_start, sub_end + 1):
                page_map[pg] = (cap_name, sub_name)
    return page_map


def apply_capitoli(df, capitoli):
    page_map = build_page_map(capitoli)
    serie_mappata = df["page_num"].map(page_map)
    df["capitolo"] = serie_mappata.str[0]
    df["sottocapitolo"] = serie_mappata.str[1]
    return df
