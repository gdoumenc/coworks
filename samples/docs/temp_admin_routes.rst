The ``Admin`` blueprint adds several routes::
  
  (project) $ curl -H "Authorization:token" http://127.0.0.1:5000/admin/route?pretty=1
  {
        "/": {
            "POST": {
                "doc": "",
                "signature": "(value=None)"
            }
        },
        "/admin/context": {
            "GET": {
                "doc": "Returns the calling context.",
                "signature": "()"
            }
        },
        "/admin/env": {
            "GET": {
                "doc": "Returns the stage environment.",
                "signature": "()"
            }
        },
        "/admin/event": {
            "GET": {
                "doc": "Returns the calling context.",
                "signature": "()"
            }
        },
        "/admin/route": {
            "GET": {
                "doc": "Returns the list of entrypoints with signature.",
                "signature": "(pretty=False)"
            }
        },
        "/profile": {
            "GET": {
                "doc": "",
                "signature": "()"
            }
        }
    }
