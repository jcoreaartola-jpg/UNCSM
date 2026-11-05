from database import connect

def teams():
    with connect() as db: return db.execute('SELECT * FROM teams ORDER BY id').fetchall()

def register(names):
    names=[n.strip() for n in names]
    if len(names)!=10 or any(not n for n in names): raise ValueError('Escribí los 10 nombres de equipos.')
    if len({n.casefold() for n in names})!=10: raise ValueError('Los nombres no pueden repetirse.')
    with connect() as db:
        if db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]: raise ValueError('El calendario ya existe. Reiniciá para cambiar equipos.')
        db.execute('DELETE FROM teams')
        db.executemany('INSERT INTO teams(name) VALUES(?)',[(n,) for n in names])

def generate():
    with connect() as db:
        ids=[r['id'] for r in db.execute('SELECT id FROM teams ORDER BY id')]
        if len(ids)!=10: raise ValueError('Primero registrá los 10 equipos.')
        if db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]: raise ValueError('El calendario ya fue generado.')
        # Método del círculo: nueve jornadas, cinco partidos por jornada.
        ring=ids[:]
        for rnd in range(1,10):
            for i in range(5):
                a,b=ring[i],ring[9-i]
                if (rnd+i)%2: a,b=b,a
                db.execute("INSERT INTO matches(phase,round_no,home_id,away_id) VALUES('liga',?,?,?)",(rnd,a,b))
            ring=[ring[0],ring[-1],*ring[1:-1]]
        db.execute("UPDATE settings SET value='1' WHERE key='calendar'")

def matches(phase=None):
    with connect() as db:
        sql='''SELECT m.*,h.name home_name,a.name away_name FROM matches m
               JOIN teams h ON h.id=m.home_id JOIN teams a ON a.id=m.away_id'''
        args=[]
        if phase: sql+=' WHERE m.phase=?'; args=[phase]
        sql+=" ORDER BY CASE phase WHEN 'liga' THEN 1 WHEN 'semi' THEN 2 ELSE 3 END,round_no,leg,id"
        return db.execute(sql,args).fetchall()

def save_result(mid,hg,ag):
    if hg<0 or ag<0: raise ValueError('Los goles no pueden ser negativos.')
    with connect() as db:
        cur=db.execute('UPDATE matches SET hg=?,ag=?,played=1,hp=NULL,ap=NULL WHERE id=?',(hg,ag,mid))
        if not cur.rowcount: raise ValueError('Partido no encontrado.')

def standings():
    with connect() as db:
        ts=db.execute('SELECT * FROM teams').fetchall()
        s={x['id']:{'id':x['id'],'name':x['name'],'PJ':0,'PG':0,'PE':0,'PP':0,'GF':0,'GC':0,'DG':0,'PTS':0} for x in ts}
        for m in db.execute("SELECT * FROM matches WHERE phase='liga' AND played=1"):
            h,a=s[m['home_id']],s[m['away_id']]; hg,ag=m['hg'],m['ag']
            h['PJ']+=1; a['PJ']+=1; h['GF']+=hg; h['GC']+=ag; a['GF']+=ag; a['GC']+=hg
            if hg>ag: h['PG']+=1; h['PTS']+=3; a['PP']+=1
            elif ag>hg: a['PG']+=1; a['PTS']+=3; h['PP']+=1
            else: h['PE']+=1; a['PE']+=1; h['PTS']+=1; a['PTS']+=1
        for x in s.values(): x['DG']=x['GF']-x['GC']
        return sorted(s.values(),key=lambda x:(-x['PTS'],-x['DG'],-x['GF'],x['name'].casefold()))

def league_done():
    with connect() as db:
        r=db.execute("SELECT COUNT(*) n,COALESCE(SUM(played),0) p FROM matches WHERE phase='liga'").fetchone()
        return r['n']==45 and r['p']==45

def create_semis():
    if not league_done(): raise ValueError('Primero completá los 45 partidos de liga.')
    top=[x['id'] for x in standings()[:4]]
    with connect() as db:
        if db.execute("SELECT COUNT(*) FROM matches WHERE phase='semi'").fetchone()[0]: return
        one,two,three,four=top
        for leg,h,a in [(1,one,four),(2,four,one),(1,two,three),(2,three,two)]:
            db.execute("INSERT INTO matches(phase,leg,home_id,away_id) VALUES('semi',?,?,?)",(leg,h,a))

def semi_winner(which):
    ms=[m for m in matches('semi')][(which-1)*2:which*2]
    if len(ms)!=2 or not all(m['played'] for m in ms): return None
    totals={ms[0]['home_id']:0,ms[0]['away_id']:0}
    for m in ms: totals[m['home_id']]+=m['hg']; totals[m['away_id']]+=m['ag']
    a,b=list(totals)
    if totals[a]>totals[b]: return a
    if totals[b]>totals[a]: return b
    # En empate global se exige tanda registrada en el partido de vuelta.
    last=ms[1]
    if last['hp'] is None or last['ap'] is None: return None
    return last['home_id'] if last['hp']>last['ap'] else last['away_id'] if last['ap']>last['hp'] else None

def save_penalties(mid,hp,ap):
    if hp<0 or ap<0 or hp==ap: raise ValueError('La tanda debe tener un ganador y valores no negativos.')
    with connect() as db:
        m=db.execute('SELECT * FROM matches WHERE id=?',(mid,)).fetchone()
        if not m or not m['played'] or m['phase'] not in ('semi','final'): raise ValueError('No se puede registrar esa tanda.')
        db.execute('UPDATE matches SET hp=?,ap=? WHERE id=?',(hp,ap,mid))

def create_final():
    a,b=semi_winner(1),semi_winner(2)
    if not a or not b: raise ValueError('Definí las dos semifinales, incluyendo penaltis si hay empate global.')
    with connect() as db:
        if not db.execute("SELECT COUNT(*) FROM matches WHERE phase='final'").fetchone()[0]:
            db.execute("INSERT INTO matches(phase,home_id,away_id) VALUES('final',?,?)",(a,b))

def champion():
    ms=matches('final')
    if not ms or not ms[0]['played']: return None
    m=ms[0]
    if m['hg']>m['ag']: wid=m['home_id']
    elif m['ag']>m['hg']: wid=m['away_id']
    elif m['hp'] is not None and m['ap'] is not None and m['hp']!=m['ap']: wid=m['home_id'] if m['hp']>m['ap'] else m['away_id']
    else: return None
    with connect() as db: return db.execute('SELECT * FROM teams WHERE id=?',(wid,)).fetchone()

def reset():
    with connect() as db:
        db.execute('DELETE FROM matches'); db.execute('DELETE FROM teams'); db.execute("UPDATE settings SET value='0' WHERE key='calendar'")
