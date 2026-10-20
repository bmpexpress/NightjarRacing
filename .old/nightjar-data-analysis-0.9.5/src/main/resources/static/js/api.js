export async function api(url,opt={}){const r=await fetch(url,{credentials:"same-origin",...opt});const type=r.headers.get("content-type")||"";const body=type.includes("json")?await r.json():r;if(!r.ok)throw new Error(body?.error||r.statusText);return body}
export const post=(url,body)=>api(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
export const upload=form=>api("/api/upload",{method:"POST",body:new FormData(form)});
