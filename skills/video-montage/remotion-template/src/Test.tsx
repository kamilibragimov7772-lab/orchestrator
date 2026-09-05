import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const Test = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 12}});
  const scale = interpolate(s, [0, 1], [0.6, 1]);
  const y = interpolate(s, [0, 1], [90, 0]);
  const op = interpolate(f, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const sub = interpolate(f, [18, 34], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: 'linear-gradient(160deg,#0b1020,#1a2747)', justifyContent: 'center', alignItems: 'center', fontFamily: 'Segoe UI, Arial, sans-serif'}}>
      <div style={{opacity: op, transform: `translateY(${y}px) scale(${scale})`, color: 'white', fontSize: 165, fontWeight: 900, letterSpacing: 6}}>ЗАГОЛОВОК</div>
      <div style={{opacity: sub, marginTop: 24, color: '#9db4e0', fontSize: 52, fontWeight: 500}}>motion-тест ✦</div>
    </AbsoluteFill>
  );
};
