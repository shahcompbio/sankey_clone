import scanpy as sc
import argparse
from jinja2 import Template
import os
import json

def get_data(adata, timepoints, threshold, timepoint, clone_id, cell_type):
    df = adata.obs[[timepoint, clone_id, cell_type]]
    df = df.reset_index()
    df = df.rename(columns={'index': 'cell_id'})
    df = df.replace(to_replace="nan", value="None")

    df = filter_data(df, timepoints, threshold, timepoint, clone_id, cell_type)
    return df

def filter_data(df, timepoints, threshold, timepoint, clone_id, cell_type):
    ## Filter out cells that are in different timepoints
    df = df[df[timepoint].isin(timepoints)]

    ## Filter out all clones that are present in all timepoint values at threshold level

    pre = df[df[timepoint] == timepoints[0]]
    pre_counts = pre[clone_id].value_counts()
    pre_clones = set(pre[pre[clone_id].isin(pre_counts[pre_counts >= threshold].index)][clone_id])


    post = df[df[timepoint] == timepoints[1]]
    post_counts = post[clone_id].value_counts()
    post_clones = set(post[post[clone_id].isin(post_counts[post_counts >= threshold].index)][clone_id])

    clones = pre_clones.intersection(post_clones)

    return df[df[clone_id].isin(clones)]

def open_data(filepath, timepoint, clone_id, subtype):
    adata = sc.read(filepath)

    assert clone_id in adata.obs.columns, 'Missing field in obs: ' + clone_id
    assert timepoint in adata.obs.columns, 'Missing field in obs: ' + timepoint
    assert subtype in adata.obs.columns, 'Missing field in obs: ' + subtype

    return adata

def get_timepoints(adata, order, timepoint):
    if order is None:
        timepoints = adata.obs[timepoint].unique()
        assert len(timepoints) == 2, timepoint + ' column does not have 2 unique values, filter data or use order argument'

        return sorted(timepoints)
    return order

def populate_html(df, dashboard_id, width, height, timepoint_param, timepoints, clone_param, subtype_param):
    data = df.to_dict(orient='records')
    app_args = {
        "data": data,
        "width": width,
        "height": height,
        "subsetParam": subtype_param,
        "cloneParam": clone_param,
        "timepointParam": timepoint_param,
        "timepointOrder": timepoints
    }

    app_json = json.dumps(app_args, indent=4)

    with open("template.html","r") as file:
        template = Template(file.read())

    html = template.render(data=app_json, dashboard="Sankey", dashboard_id=dashboard_id)

    with open(f"sankey_{dashboard_id}.html", 'w') as output_file:
        output_file.write(html)

parser = argparse.ArgumentParser(description='Output sankey HTML with data file')
parser.add_argument('dashboard_id', type=str)
parser.add_argument('path', type=str)
parser.add_argument('-t', '--threshold', type=int, help='Minimum number of cells present in a clone in each timepoint to be included', default=3)
parser.add_argument('-o', '--order', type=str, nargs=2, help='Order of timepoints')
parser.add_argument('--width', type=int, default=800, help='Pixel width of sankey plot')
parser.add_argument('--height', type=int, default=700, help='Pixel height of sankey plot')
parser.add_argument('--timepoint', type=str, default='timepoint', help='Column name for timepoint')
parser.add_argument('--clone', type=str, default='clone_id', help='Column name for clone ID')
parser.add_argument('--subtype', type=str, default='cell_type', help='Column name for cell type')

args = parser.parse_args()

assert args.threshold > 0, 'Input threshold of at least 1'

adata = open_data(args.path, args.timepoint, args.clone, args.subtype)

timepoints = get_timepoints(adata, args.order, args.timepoint)

data = get_data(adata, timepoints, args.threshold, args.timepoint, args.clone, args.subtype)

populate_html(data, args.dashboard_id, args.width, args.height, args.timepoint, timepoints, args.clone, args.subtype)