import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, Series,
  Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import data from './data.json';

export const FPS = data.fps;
export const WIDTH = data.w;
export const HEIGHT = data.h;

const introF = data.introF;
const outroF = data.outroF;
const bodyF = Math.round(data.clips.reduce((a, c) => a + c.dur, 0) * FPS);
export const totalDurationInFrames = introF + bodyF + outroF;

const FONT = 'Segoe UI, Arial, sans-serif';

// intro/outro card texts come from data.json (title / subtitle / caption / outro)
const d: any = data;
const TITLE = d.title || 'ЗАГОЛОВОК';
const SUBTITLE = d.subtitle || 'подзаголовок ролика';
const CAPTION = d.caption || 'месяц · год';
const OUTRO = d.outro || 'спасибо за внимание';

const CHUNKS = (() => {
  const out: any[] = [];
  let cur: any[] = [];
  for (const w of data.words as any[]) {
    if (!cur.length) cur = [w];
    else if (cur.length >= 5 || (w.e - cur[0].s) > 2.4) { out.push(cur); cur = [w]; }
    else cur.push(w);
  }
  if (cur.length) out.push(cur);
  return out;
})();

// clip with eased camera move (zoom + drift) for depth, not a flat hold
const Clip = ({file, durF, dir}: {file: string; durF: number; dir: number}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 7], [0, 1], {extrapolateRight: 'clamp'});
  const p = interpolate(f, [0, durF], [0, 1], {extrapolateRight: 'clamp', easing: Easing.inOut(Easing.ease)});
  const scale = interpolate(p, [0, 1], [1.12, 1.0]);
  const driftX = interpolate(p, [0, 1], [dir * 34, 0]);
  const isVideo = /\.(mov|mp4)$/i.test(file);
  return (
    <AbsoluteFill style={{backgroundColor: 'black', opacity: op, overflow: 'hidden'}}>
      <div style={{width: '100%', height: '100%', transform: `scale(${scale}) translateX(${driftX}px)`}}>
        {isVideo ? (
          <OffthreadVideo src={staticFile(file)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        ) : (
          <Img src={staticFile(file)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        )}
      </div>
    </AbsoluteFill>
  );
};

const Intro = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 9, mass: 0.9}}); // overshoot
  const rotX = interpolate(s, [0, 1], [-78, 0]);
  const y = interpolate(s, [0, 1], [60, 0]);
  const op = interpolate(f, [0, 10], [0, 1], {extrapolateRight: 'clamp'});
  const sub = interpolate(f, [18, 34], [0, 1], {extrapolateRight: 'clamp'});
  const subX = interpolate(spring({frame: Math.max(0, f - 16), fps, config: {damping: 12}}), [0, 1], [-60, 0]);
  const out = interpolate(f, [introF - 14, introF], [1, 0], {extrapolateLeft: 'clamp'});
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 90% at 50% 35%,#22386b 0%,#0b1020 70%)', justifyContent: 'center', alignItems: 'center', fontFamily: FONT, opacity: out}}>
      <div style={{perspective: 1000}}>
        <div style={{opacity: op, transform: `translateY(${y}px) rotateX(${rotX}deg)`, color: '#fff', fontSize: 168, fontWeight: 900, letterSpacing: 6, textShadow: '0 18px 50px rgba(80,130,255,.55), 0 0 30px rgba(120,160,255,.45)'}}>{TITLE}</div>
      </div>
      <div style={{opacity: sub, transform: `translateX(${subX}px)`, marginTop: 24, color: '#cdd9f5', fontSize: 50, fontWeight: 600}}>{SUBTITLE}</div>
      <div style={{opacity: sub, transform: `translateX(${-subX}px)`, marginTop: 8, color: '#7e95c4', fontSize: 36}}>{CAPTION}</div>
    </AbsoluteFill>
  );
};

const Outro = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 10, mass: 0.9}});
  const sc = interpolate(s, [0, 1], [0.7, 1]);
  const rotX = interpolate(s, [0, 1], [40, 0]);
  const op = interpolate(f, [0, 14], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 90% at 50% 60%,#22386b 0%,#0b1020 70%)', justifyContent: 'center', alignItems: 'center', fontFamily: FONT}}>
      <div style={{perspective: 1000}}>
        <div style={{opacity: op, transform: `scale(${sc}) rotateX(${rotX}deg)`, color: '#fff', fontSize: 94, fontWeight: 800, textShadow: '0 14px 40px rgba(80,130,255,.5)'}}>{OUTRO}</div>
      </div>
    </AbsoluteFill>
  );
};

const Captions = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = (f - introF) / fps;
  const chunk = CHUNKS.find((c) => t >= c[0].s - 0.15 && t <= c[c.length - 1].e + 0.35);
  if (!chunk) return null;
  const ap = interpolate(t, [chunk[0].s - 0.15, chunk[0].s + 0.12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 360, perspective: 1100}}>
      <div style={{maxWidth: 930, textAlign: 'center', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '4px 18px', opacity: ap, transform: `translateY(${interpolate(ap, [0, 1], [44, 0])}px) rotateX(${interpolate(ap, [0, 1], [28, 0])}deg)`}}>
        {chunk.map((w: any, i: number) => {
          const on = t >= w.s;
          const pop = on ? interpolate(t, [w.s, w.s + 0.1, w.s + 0.24], [1, 1.26, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
          const rx = on ? interpolate(t, [w.s, w.s + 0.2], [40, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
          return (
            <span key={i} style={{
              fontFamily: FONT, fontWeight: 800, fontSize: 86, lineHeight: 1.12,
              color: on ? '#ffd23f' : '#ffffff',
              transform: `perspective(600px) rotateX(${rx}deg) scale(${pop})`, display: 'inline-block',
              textShadow: on ? '0 6px 22px rgba(0,0,0,.7), 0 0 26px rgba(255,200,60,.6)' : '0 6px 20px rgba(0,0,0,.7)',
              WebkitTextStroke: '3px rgba(8,10,20,.85)',
            }}>{w.t}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Inserts = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = (f - introF) / fps;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: 290, perspective: 1200}}>
      {(data.inserts as any[]).map((ins, i) => {
        const dt = t - ins.t;
        if (dt < -0.1 || dt > 2.0) return null;
        const lf = dt * fps;
        const s = spring({frame: lf, fps, config: {damping: 9, mass: 0.7}}); // bouncy
        const sc = interpolate(s, [0, 1], [0.1, 1]);
        const rotY = interpolate(s, [0, 1], [120, 0]);
        const fade = interpolate(dt, [0, 0.18, 1.6, 2.0], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const floatY = interpolate(dt, [0, 2.0], [10, -48], {easing: Easing.out(Easing.ease)});
        const glow = 14 + 12 * Math.sin(dt * 7); // pulsing ring
        return (
          <div key={i} style={{position: 'absolute', opacity: fade, transform: `translateY(${floatY}px) scale(${sc})`, transformStyle: 'preserve-3d'}}>
            <div style={{
              width: 210, height: 210, borderRadius: 110, transform: `rotateY(${rotY}deg)`,
              background: 'linear-gradient(150deg, rgba(40,60,120,.78), rgba(12,16,32,.7))',
              border: '4px solid rgba(255,255,255,.92)',
              display: 'flex', justifyContent: 'center', alignItems: 'center',
              boxShadow: `0 18px 50px rgba(0,0,0,.55), 0 0 ${glow}px rgba(130,170,255,.85)`,
            }}>
              <span style={{fontSize: 122, lineHeight: 1}}>{ins.emoji}</span>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const Moscow = () => {
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <Sequence from={0} durationInFrames={introF}><Intro /></Sequence>

      <Sequence from={introF}>
        <Series>
          {(data.clips as any[]).map((c, i) => (
            <Series.Sequence key={i} durationInFrames={Math.max(1, Math.round(c.dur * FPS))}>
              <Clip file={c.file} durF={Math.round(c.dur * FPS)} dir={i % 2 === 0 ? 1 : -1} />
            </Series.Sequence>
          ))}
        </Series>
      </Sequence>

      <Captions />
      <Inserts />

      <Sequence from={introF + bodyF} durationInFrames={outroF}><Outro /></Sequence>

      <Sequence from={introF}>
        <Audio src={staticFile(data.audio)} volume={(ff) => interpolate(ff, [0, 20, Math.round(data.voice * FPS) - 40, Math.round(data.voice * FPS)], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />
      </Sequence>
    </AbsoluteFill>
  );
};
