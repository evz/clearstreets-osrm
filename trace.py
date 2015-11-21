import requests
import sqlalchemy as sa
import json


def iterAssets():
    engine = sa.create_engine('postgresql://eric:@localhost:5432/plows')
    
    asset_ids = ''' SELECT * FROM assets '''
    
    trace = ''' 
        SELECT 
          ST_X(geom) AS lon,
          ST_Y(geom) AS lat,
          posting_time
        FROM route_points
        WHERE object_id = :object_id
        ORDER BY posting_time
    '''

    for asset in engine.execute(asset_ids):

        asset_trace = []
        for row in engine.execute(sa.text(trace), 
                                  object_id=asset.object_id):

            asset_trace.append([asset, row])
        
        yield asset_trace

def matchRoutes():
    
    base_url = 'http://localhost:5000/match' 
    point_fmt = 'loc={lat},{lon}&t={timestamp}'

    for trace in iterAssets():
        query = []
        
        for asset, row in trace:
            posting_timestamp = int(row.posting_time.timestamp())
            
            point_query = point_fmt.format(lat=row.lat, 
                                           lon=row.lon, 
                                           timestamp=posting_timestamp)
            query.append(point_query)

        query = '&'.join(query)

        trace_resp = requests.get('{0}?compression=false&{1}'.format(base_url, query))
        
        asset_geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        try:
            matchings = trace_resp.json()['matchings']
        except KeyError:
            matchings = []

        for match in matchings:
            geometry = []
            
            for lat, lng in match['geometry']:
                geometry.append([lng, lat])

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': geometry,
                },
                'properties': dict(zip(asset.keys(), asset.values()))
            }
            asset_geojson['features'].append(feature)

        with open('{0}.geojson'.format(asset.object_id), 'w') as f:
            f.write(json.dumps(asset_geojson))
        
        print('wrote out', asset.object_id)

if __name__ == "__main__":
    matchRoutes()
