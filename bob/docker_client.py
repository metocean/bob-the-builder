import docker


def clean_all_networks():
    c = docker.Client()

    for net in c.networks():
        if net['Name'] in ('bridge', 'host', 'none'):
            continue

        for con_id in net['Containers']:
            c.stop(con_id)

        c.remove_network(net['Id'])

