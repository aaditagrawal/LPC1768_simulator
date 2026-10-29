import {test,expect,type Page} from '@playwright/test';

test.beforeEach(async({request})=>{
 const state=await (await request.get('/api/state')).json();
 await request.post('/api/control',{data:{action:'stop'}});
 await request.post('/api/physical',{data:{action:'release-inputs'}});
 for(const [header] of state.cables)await request.post('/api/physical',{data:{action:'disconnect',header}});
});

async function expectBoardFits(page:Page){
 await expect(page.getByLabel('Interactive ALS LPC1768 evaluation board',{exact:true})).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>{
  const root=document.documentElement;
  const board=document.querySelector('.board')!.getBoundingClientRect();
  const panel=document.querySelector('.board-scroll')!;
  const footer=document.querySelector('footer')!.getBoundingClientRect();
  return root.scrollWidth<=innerWidth+1&&root.scrollHeight<=innerHeight+1
   &&board.left>=0&&board.top>=0&&board.right<=innerWidth+1&&board.bottom<=innerHeight+1
   &&board.height>120&&footer.bottom<=innerHeight+1
   &&panel.scrollWidth<=panel.clientWidth+1&&panel.scrollHeight<=panel.clientHeight+1;
 })).toBe(true);
}

test('the complete board fits the viewport and resizes without page or board scrolling',async({page})=>{
 await page.goto('/#board');
 for(const [width,height] of [[1366,768],[1093,614],[1920,1080],[1280,600],[1024,768],[800,450],[2560,1440],[3840,2160],[390,844]]){
  await page.setViewportSize({width,height});
  await expectBoardFits(page);
 }
});

test('Fit restores the complete board after zooming with firmware and cables loaded',async({page})=>{
 await page.setViewportSize({width:1366,height:768});
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill('#include <LPC17xx.h>\nint main(void){while(1){}}');
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await expect(page.getByRole('button',{name:'Compile C',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('link',{name:'Board',exact:true}).click();
 for(const [from,to] of [['CNA','CNA2'],['CNB','CNB2'],['CND','CNB1']]){
  await page.getByRole('button',{name:`Header ${from}`,exact:true}).click();
  await page.getByRole('button',{name:`Header ${to}`,exact:true}).click();
 }
 await expect(page.getByRole('button',{name:'Disconnect cable CNA to CNA2',exact:true})).toBeVisible();
 await expectBoardFits(page);
 await page.getByLabel('Board zoom').fill('180');
 await expect.poll(()=>page.locator('.board-scroll').evaluate(el=>el.scrollHeight>el.clientHeight)).toBe(true);
 await page.getByRole('button',{name:'Fit board to screen',exact:true}).click();
 await expect(page.getByLabel('Board zoom')).toHaveValue('100');
 await expectBoardFits(page);
 await page.getByRole('button',{name:'Disconnect cable CNA to CNA2',exact:true}).click();
 await expect(page.getByRole('button',{name:'Disconnect cable CNA to CNA2',exact:true})).toHaveCount(0);
 await page.setViewportSize({width:800,height:450});
 await expectBoardFits(page);
});
