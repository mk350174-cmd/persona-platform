import React, { useState, useRef } from 'react';

export default function VoicePreview({ personaId, personaName, voiceUrl }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef(null);

  const handlePlay = () => {
    if (audioRef.current) {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
  };

  const handleSliderChange = (e) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Sample voice URL for demo
  const sampleVoiceUrl = voiceUrl || `data:audio/mp3;base64,//NExAAMIAIADAA8CAAAAAATQZX0AAAANGQBH/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x//H/8f/x`;

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="glass-panel rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline-md text-on-surface">Voice Preview</h3>
        <span className="text-xs px-3 py-1 rounded-full bg-primary-container/20 text-primary">
          5 sec sample
        </span>
      </div>

      <p className="text-on-surface-variant text-sm">
        Hear how {personaName} sounds
      </p>

      {/* Audio Element */}
      <audio
        ref={audioRef}
        src={sampleVoiceUrl}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
      />

      {/* Player Controls */}
      <div className="space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={isPlaying ? handlePause : handlePlay}
            className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-container text-white hover:opacity-90 transition-opacity"
          >
            <span className="material-symbols-outlined">
              {isPlaying ? 'pause' : 'play_arrow'}
            </span>
          </button>

          <div className="flex-1">
            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleSliderChange}
              className="w-full h-2 bg-surface-container rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <span className="text-sm text-on-surface-variant font-mono-data min-w-10 text-right">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>

        {/* Voice Characteristics */}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div className="bg-surface-container-high rounded-lg p-3 text-center">
            <p className="text-on-surface-variant text-xs mb-1">Tone</p>
            <p className="text-on-surface font-semibold">Thoughtful</p>
          </div>
          <div className="bg-surface-container-high rounded-lg p-3 text-center">
            <p className="text-on-surface-variant text-xs mb-1">Pace</p>
            <p className="text-on-surface font-semibold">Measured</p>
          </div>
          <div className="bg-surface-container-high rounded-lg p-3 text-center">
            <p className="text-on-surface-variant text-xs mb-1">Gender</p>
            <p className="text-on-surface font-semibold">Neutral</p>
          </div>
        </div>
      </div>
    </div>
  );
}
