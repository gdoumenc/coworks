import os

import requests


class CosmicCmsClient:

    def __init__(self, **kwargs):
        self.base_url = "https://api.cosmicjs.com/v1"
        self.bucket = os.getenv('COSMICJS_BUCKET')
        self.read_token = os.getenv('COSMICJS_READ_TOKEN')

    def object_metafields(self, slug):
        response = self.object(slug)
        if response is None:
            return {}
        return {k: v for d in response['metafields'] for k, v in self.to_dict(d).items()}

    def object(self, slug: str):
        """Get a specific object according its object-type and filters set in filter_metadata param."""
        url = f"{self.base_url}/{self.bucket}/object/{slug}"
        r = requests.get(url, params={
            'read_key': self.read_token,
            'props': 'title,slug,content,metadata.model,metafields',
        })
        object = r.json()['object'] if r.status_code == 200 else None
        return object

    def objects(self, slug: str):
        """Get a specific object according its object-type and filters set in filter_metadata param."""
        url = f"{self.base_url}/{self.bucket}/objects"
        r = requests.get(url, params={
            'read_key': self.read_token,
            'type': slug,
            'props': 'title,slug,content,metadata.model,metafields',
        })
        objects = r.json()['objects'] if r.status_code == 200 else None
        return objects or []

    def fields(self, response):
        return {k: v for field in response['metafields'] for k, v in self.to_dict(field).items()}

    def to_dict(self, data):
        if 'metafields' in data:
            metafields = {k: v for d in data['metafields'] for k, v in self.to_dict(d).items()}
            metafields.update({'slug': data['slug']})
            if 'content' not in metafields:
                metafields.update({'content': data['content']})
            return metafields

        type_ = data['type']
        if type_ == 'parent':
            return {data['key']: {k: v for child in data['children'] for k, v in self.to_dict(child).items()}}
        if type_ == 'objects':
            return {data['key']: [self.to_dict(obj) for obj in data.get('objects', [])]}
        if type_ == 'repeater':
            return {data['key']: [self.to_dict(child) for child in data.get('children', [])]}
        if type_ == 'repeating_item':
            return {k: v for child in data['children'] for k, v in self.to_dict(child).items()}
        return {data['key']: data['value']}
