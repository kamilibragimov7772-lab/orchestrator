import {Composition} from 'remotion';
import {Moscow, FPS, WIDTH, HEIGHT, totalDurationInFrames} from './Moscow';
import {Test} from './Test';

export const RemotionRoot = () => {
  return (
    <>
      <Composition id="Test" component={Test} durationInFrames={90} fps={30} width={1080} height={1920} />
      <Composition
        id="Moscow"
        component={Moscow}
        durationInFrames={totalDurationInFrames}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
