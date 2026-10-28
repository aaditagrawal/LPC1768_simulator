import {test,expect} from '@playwright/test';

test('manual-confirmed jumper pins and shunts show the selected physical pair',async({page})=>{
 await page.goto('/#board');
 for(const [name,count] of [['JP4',3],['JP5',2],['JP16',2],['JP18',3]] as const){
  await page.getByLabel(`${name} position`).selectOption('open');
  const jumper=page.getByRole('button',{name:`Jumper ${name} open`,exact:true});
  await expect(jumper.locator('[data-pin]')).toHaveCount(count);
  await expect(jumper.locator('[data-shunt]')).toHaveCount(0);
  for(const position of count===3?['1-2','2-3']:['closed']){
   await page.getByLabel(`${name} position`).selectOption(position);
   const selected=page.getByRole('button',{name:`Jumper ${name} ${position}`,exact:true});
   const covered=await selected.evaluate(el=>{
    const shunt=el.querySelector('[data-shunt]') as SVGGraphicsElement;
    const box=shunt.getBBox();
    return [...el.querySelectorAll('[data-pin]')].filter(pin=>{
     const b=(pin as SVGGraphicsElement).getBBox(),x=b.x+b.width/2;
     return x>box.x&&x<box.x+box.width;
    }).map(pin=>Number(pin.getAttribute('data-pin')));
   });
   expect(covered).toEqual(position==='2-3'?[2,3]:[1,2]);
  }
 }
 for(const name of ['JP7','JP8','JP12','JP13','JP17']){
  await expect(page.locator(`[data-physical-jumper="${name}"] [data-pin]`)).toHaveCount(3);
 }
});

test('active jumpers remain visible and clickable with older service metadata',async({page})=>{
 await page.route('**/api/info',async route=>{
  const response=await route.fetch();
  const info=await response.json();
  for(const jumper of Object.values(info.board.jumpers) as Record<string,unknown>[])delete jumper.pinCount;
  await route.fulfill({response,json:info});
 });
 await page.goto('/#board');
 for(const [name,count] of [['JP4',3],['JP5',2],['JP16',2],['JP18',3]] as const){
  await page.getByLabel(`${name} position`).selectOption('open');
  const jumper=page.getByRole('button',{name:`Jumper ${name} open`,exact:true});
  await expect(jumper.locator('[data-pin]')).toHaveCount(count);
  await expect(jumper.locator('.jumper-hit-area')).toHaveAttribute('width',String(count*12+16));
  await jumper.click();
  const closed=count===3?'1-2':'closed';
  await expect(page.getByLabel(`${name} position`)).toHaveValue(closed);
  await page.getByRole('button',{name:`Jumper ${name} ${closed}`,exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByLabel(`${name} position`)).toHaveValue(count===3?'2-3':'open');
 }
});

test('additional selectors have movable shunts that survive navigation without changing firmware routing',async({page,request})=>{
 await page.goto('/#board');
 const before=await (await request.get('/api/state')).json();
 for(const name of ['JP7','JP8','JP12','JP13','JP17']){
  const open=page.getByRole('button',{name:`Jumper ${name} open`,exact:true});
  await open.locator('[data-pin="2"]').click({timeout:2000});
  const first=page.getByRole('button',{name:`Jumper ${name} 1-2`,exact:true});
  await expect(first.locator('[data-shunt]')).toHaveAttribute('data-shunt','1-2');
  await first.focus();await page.keyboard.press('Space');
  await expect(page.getByRole('button',{name:`Jumper ${name} 2-3`,exact:true}).locator('[data-shunt]')).toHaveAttribute('data-shunt','2-3');
 }
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.reload();
 for(const name of ['JP7','JP8','JP12','JP13','JP17']){
  const selected=page.getByRole('button',{name:`Jumper ${name} 2-3`,exact:true});
  await expect(selected.locator('[data-shunt]')).toHaveAttribute('data-shunt','2-3');
  await selected.click();
  await expect(page.getByRole('button',{name:`Jumper ${name} open`,exact:true}).locator('[data-shunt]')).toHaveCount(0);
 }
 const after=await (await request.get('/api/state')).json();
 for(const key of ['jumpers','cables','loaded','status'])expect(after[key]).toEqual(before[key]);
});
