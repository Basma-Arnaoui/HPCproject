import dash
from dash import html, dcc, Output, Input, State
import subprocess

# Initialize the Dash app
app = dash.Dash(__name__)
app.suppress_callback_exceptions = True

# Replace this with your actual list of nodes
list_of_nodes = [
    "node01", "node02", "node03", "node04", "node05",
    "node06", "node07", "node08", "node09", "node10",
    "node11", "node12", "node13", "node14", "node15",
    "node16", "node17"
]

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

login_layout = html.Div([
    html.H2('Login'),
    dcc.Input(id='username', type='text', placeholder='Username'),
    dcc.Input(id='password', type='password', placeholder='Password'),
    html.Button('Login', id='login-button'),
    html.Div(id='login-output')
])

node_page_layout = html.Div([
    dcc.Dropdown(
        id='node-selector',
        options=[{'label': node, 'value': node} for node in list_of_nodes],
        value=list_of_nodes[0]
    ),
    html.Div(id='node-details')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/nodes':
        return node_page_layout
    else:
        return login_layout

@app.callback(
    Output('url', 'pathname'),
    [Input('login-button', 'n_clicks')],
    [State('username', 'value'), State('password', 'value')])
def login(n_clicks, username, password):
    if n_clicks:
        return '/nodes'
    return dash.no_update

@app.callback(
    Output('node-details', 'children'),
    [Input('node-selector', 'value')])
def update_node_details(selected_node):
    try:
        ssh_command = f"ssh username@slurm-server scontrol show node {selected_node}"
        result = subprocess.check_output(ssh_command, shell=True, text=True)
        details = []
        for line in result.splitlines():
            details.append(html.P(line))
        return details
    except subprocess.CalledProcessError as e:
        return html.Div(f"Error fetching details for node {selected_node}: {str(e)}")

if __name__ == '__main__':
    app.run_server(debug=True)
