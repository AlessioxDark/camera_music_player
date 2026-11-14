import React from "react";
import NextIcon from "./NextIcon";
import PauseIcon from "./PauseIcon";
import PlayIcon from "./PlayIcon";

const Player = ({ isPlaying, setIsPlaying, currentSong }) => {
  return (
    <div className="absolute bottom-6 bg-[#1e1e1e]/80 backdrop-blur-md px-4 py-3 rounded-2xl flex flex-col items-center justify-center gap-4 z-10 min-w-xl min-h-32">
      <h1 className="text-white font-bold">{currentSong.name || ""}</h1>
      <div className="flex flex-row max-w-xl items-center justify-center gap-12">
        <div className="bg-white p-3 rounded-full rotate-[180deg] cursor-pointer hover:bg-gray-200 transition">
          <NextIcon size={24} />
        </div>
        <div className="bg-white p-3 rounded-full cursor-pointer hover:bg-gray-200 transition">
          {isPlaying ? <PauseIcon size={24} /> : <PlayIcon size={24} />}
        </div>
        <div className="bg-white p-3 rounded-full cursor-pointer hover:bg-gray-200 transition">
          <NextIcon size={24} />
        </div>
      </div>
    </div>
  );
};

export default Player;
