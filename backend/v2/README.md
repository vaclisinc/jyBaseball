We aim to reorganize our strucutre from Google script API(api) + Google sheets(database) + python(backend) --> using fastapi, uvicorn, nginx(api) + SQL (database) + python (backend).

To implement this goal, we want to first change the api from google script api to fastapi, uvicorn, nginx in this version.

I already constucted a freeBSD environment in vmware to simulate the case when I really own a server. I'll first use write an code and using uvicorn to run in 0.0.0.0:8000. Then, I'll use nginx as reverse proxy to redirect my domain name and public ip to the localhost in my freeBS