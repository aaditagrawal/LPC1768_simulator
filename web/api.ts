export async function api<T>(path:string,data?:unknown):Promise<T> {
 const res=await fetch(path,data===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const text=await res.text();
 let value;
 try {value=JSON.parse(text);} catch {throw new Error(`Local server returned ${res.status}. Start the Python backend.`);}
 if(!res.ok) throw new Error(value.error||`Request failed (${res.status})`);
 return value as T;
}
