// Use immutable card IDs, including old saved records, rather than trusting an image URL.
export function tarotImagePath(card){
  const match=/^(major|wands|cups|swords|pentacles)_(\d{2})$/.exec(card?.id||'');
  if(!match)return null;
  const [,suit,digits]=match,n=Number(digits);
  if(suit==='major'?(n>21):(n<1||n>14))return null;
  const prefix={major:'m',wands:'w',cups:'c',swords:'s',pentacles:'p'}[suit];
  return `/assets/tarot-rws/${prefix}${digits}.jpg`;
}
