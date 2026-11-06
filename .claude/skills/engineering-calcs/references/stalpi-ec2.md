# Stâlpi - SR EN 1992-1-1

Normă: SR EN 1992-1-1 · Status: NEVALIDAT · Validat la: -
Proveniență: valorile folosite în `ColumnDesign.py` (prototip SeismicColumn). De verificat cu textul normei și cu Anexa Națională.

| ID | Regulă | Valoare / formulă | Articol | Observații |
|---|---|---|---|---|
| EC2-COL-IMPERF | imperfecțiuni | ei = l0/400 | 5.2(9) | variantă simplificată |
| EC2-COL-E0 | excentricitate minimă | e0 = max(h/30; 20 mm) | 6.1(4) | |
| EC2-COL-LAMBDA-LIM | zveltețe limită | λlim = 20·A·B·C/√n, A = 0,7, B = 1,1, C = 0,7 | 5.8.3.1 | C = 0,7 ales acoperitor (cadre necontravântuite) |
| EC2-COL-CURV | curbura nominală | 1/r = Kr·Kφ·εyd/(0,45·d), Kφ = 1, Kr = (1+ω−n)/(1+ω−0,4) ≤ 1 | 5.8.8.3 | Kφ = 1 neglijează fluajul - de verificat |
| EC2-COL-E2 | excentricitate de ordinul 2 | e2 = (1/r)·l0²/10 | 5.8.8.2 | c = 10 |
| EC2-COL-MED | moment de calcul | MEd = max(|M02| + N·ei + N·e2; N·e0) | 5.8.8.2 | simplificare acoperitoare față de M0e |
| EC2-COL-BIAX | încovoiere oblică | (MEdx/MRdx)^a + (MEdy/MRdy)^a ≤ 1; a = 1,0 / 1,5 / 2,0 la NEd/NRd = 0,1 / 0,7 / 1,0 | 5.8.9(4) | NRd = Ac·fcd + As·fyd |
| EC2-COL-AS-MIN | armare longitudinală minimă | As,min = max(0,10·NEd/fyd; 0,002·Ac) | 9.5.2(2) | valori din Anexa Națională - de verificat |
| EC2-COL-AS-MAX | armare longitudinală maximă | 0,04·Ac (în afara înnădirilor) | 9.5.2(3) | |
| EC2-COL-CLEAR | distanța liberă între bare | ≥ max(Ø; dg + 5 mm; 20 mm) | 8.2(2) | |
| EC2-COL-STIRRUP-D | diametrul etrierilor | ≥ max(6 mm; Ø/4) | 9.5.3(1) | |
| EC2-COL-STIRRUP-S | distanța între etrieri (zona curentă) | ≤ min(20·Ømin; bmin; 400 mm) | 9.5.3(3) | valoarea din Anexa Națională - de verificat |
| EC2-COL-VRDS | rezistența etrierilor | VRd,s = Asw/s·z·fywd·cot θ, z = 0,9·d | 6.2.3(3) | |
| EC2-COL-VRDMAX | rezistența bielelor | VRd,max = αcw·bw·z·ν1·fcd/(cot θ + tan θ), αcw = 1, ν1 = 0,6·(1 − fck/250) | 6.2.3(3) | αcw = 1 acoperitor |
| EC2-COL-COT | cot θ | 1 ≤ cot θ ≤ 2,5 | 6.2.3(2) | |
| EC2-COL-LB | lungimea de ancorare de bază | lb,rqd = (Ø/4)·σsd/fbd, σsd = fyd | 8.4.3 | |
| EC2-COL-L0 | lungimea de suprapunere | l0 = α6·lb,rqd, α1..α5 = 1, α6 = 1,5; l0 ≥ max(0,3·α6·lb,rqd; 15·Ø; 200 mm) | 8.7.3 | 100 % bare înnădite în aceeași secțiune |
