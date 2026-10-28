/** Export the current local board as a self-contained SVG and PNG preview. */
import {chromium} from 'playwright';
import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const target=process.argv[2]||'http://127.0.0.1:8765';
const browser=await chromium.launch();
try {
 const page=await browser.newPage({viewport:{width:1800,height:1200}});
 await page.goto(target);
 const board=page.getByLabel('Interactive ALS LPC1768 evaluation board',{exact:true});
 await board.waitFor();
 const svg=await board.evaluate(element=>{
  const copy=element.cloneNode(true);
  const [, ,width,height]=element.getAttribute('viewBox').split(/\s+/);
  copy.setAttribute('width',width);
  copy.setAttribute('height',height);
  copy.removeAttribute('class');
  // Cable labels use stylesheet rules in the app; embed their appearance for export.
  for(const text of copy.querySelectorAll('.cable-number')){
   text.setAttribute('style','font:bold 15px Consolas,monospace;fill:#f8f7df;stroke:#14251c;stroke-width:4px;paint-order:stroke');
  }
  return '<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(copy);
 });
 await writeFile(new URL('../board/board.svg',import.meta.url),svg,'utf8');
 await board.screenshot({path:fileURLToPath(new URL('../build/vector-board-preview.png',import.meta.url))});
 console.log('Exported board/board.svg and build/vector-board-preview.png');
} finally {
 await browser.close();
}
