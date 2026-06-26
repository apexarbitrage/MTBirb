/*
 * Records a short mic clip and encodes it as a mono 16-bit WAV at the device's native sample
 * rate (BirdNET/librosa resamples server-side, so we don't need to). Sending WAV keeps the
 * backend free of ffmpeg. Uses ScriptProcessorNode - deprecated but still the simplest broadly
 * supported way to grab raw PCM without a separate AudioWorklet module.
 */

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  let length = 0;
  for (const c of chunks) length += c.length;
  const view = new DataView(new ArrayBuffer(44 + length * 2));
  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, length * 2, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++) {
      const s = Math.max(-1, Math.min(1, chunk[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([view], { type: "audio/wav" });
}

export async function recordWavClip(
  seconds: number,
  onLevel?: (rms: number) => void,
): Promise<Blob> {
  // getUserMedia only exists in a secure context (https:// or localhost). Over plain HTTP on a
  // LAN IP - e.g. opening the dev server from a phone - navigator.mediaDevices is undefined, so
  // guard with a clear message instead of letting it throw "undefined is not an object".
  const media = navigator.mediaDevices;
  if (!media || typeof media.getUserMedia !== "function") {
    throw new Error(
      window.isSecureContext === false
        ? "Microphone needs a secure connection — open the app over https:// or on localhost, not a plain http:// LAN address."
        : "This browser doesn't support microphone capture.",
    );
  }
  const stream = await media.getUserMedia({ audio: true });
  const AudioCtor =
    window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioCtor();
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const muted = ctx.createGain();
  muted.gain.value = 0; // route to destination (so it runs) without audible feedback
  const chunks: Float32Array[] = [];

  return new Promise<Blob>((resolve) => {
    processor.onaudioprocess = (e) => {
      const data = e.inputBuffer.getChannelData(0);
      chunks.push(new Float32Array(data));
      if (onLevel) {
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
        onLevel(Math.sqrt(sum / data.length));
      }
    };
    source.connect(processor);
    processor.connect(muted);
    muted.connect(ctx.destination);

    setTimeout(() => {
      processor.disconnect();
      source.disconnect();
      muted.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      const wav = encodeWav(chunks, ctx.sampleRate);
      void ctx.close();
      resolve(wav);
    }, seconds * 1000);
  });
}
