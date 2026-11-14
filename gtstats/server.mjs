import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
const port=Number(process.env.PORT||3000),data=process.env.DATA_FILE||'/data/stats.json';
const root=new URL('./public/',import.meta.url).pathname;
const assets={'/':'index.html','/app.js':'app.js','/style.css':'style.css'};
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
http.createServer(async(req,res)=>{
 res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','same-origin');
 res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");
 const url=new URL(req.url,'http://localhost');
 if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);return res.end();}
 try{
  if(url.pathname==='/healthz') {await fs.access(data);res.writeHead(200,{'Content-Type':'application/json'});return res.end('{"ok":true}');}
  if(url.pathname==='/api/stats'){
   const raw=await fs.readFile(data);JSON.parse(raw);res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});return res.end(req.method==='HEAD'?undefined:raw);
  }
  const file=assets[url.pathname];if(!file){res.writeHead(404);return res.end('Not found');}
  const raw=await fs.readFile(path.join(root,file));res.writeHead(200,{'Content-Type':types[path.extname(file)],'Cache-Control':'no-cache'});res.end(req.method==='HEAD'?undefined:raw);
 }catch(e){res.writeHead(503,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end('{"error":"Stats are temporarily unavailable. Please try again shortly."}');}
}).listen(port,'0.0.0.0',()=>console.log(`GTStats listening on ${port}`));
