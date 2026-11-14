import { useEffect, useRef, useState } from "react";

import Player from "./components/Player";
function App() {
  const videoRef = useRef();
  const audioRef = useRef(null); // <--- Riferimento per il tag audio HTML5
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSong, setCurrentSong] = useState({
    name: "Nessun brano in riproduzione",
    artist: "-",
    albumArt: "",
    dati: "",
    index: 0,
  });
  const [volume, setVolume] = useState(0);
  const [playListData, setPlaylistData] = useState([]);
  const playlistRef = useRef([]);
  playlistRef.current = playListData;

  const currentSongRef = useRef(currentSong);
  currentSongRef.current = currentSong;

  const volumeRef = useRef(volume); // <--- Riferimento per il tag audio HTML5
  volumeRef.current = volume;
  useEffect(() => {
    // 1. ALL'AVVIO: Chiediamo la playlist a Python tramite la Promise
    const avviaApp = async () => {
      while (!window.pywebview || !window.pywebview.api) {
        await new Promise((resolve) => setTimeout(resolve, 300));
      }

      try {
        const datiIniziali = await window.pywebview.api.ready();
        setPlaylistData(datiIniziali.playlist);

        // Impostiamo la prima canzone corrente se la playlist non è vuota
        if (datiIniziali.playlist && datiIniziali.playlist.length > 0) {
          const branoIniziale =
            datiIniziali.playlist[datiIniziali.currentIndex || 0];
          setCurrentSong({
            name: branoIniziale.name,
            artist: branoIniziale.artist || "Local File",
            albumArt: branoIniziale.albumArt || "",
            dati: branoIniziale.dati || "",

            index: 0,
          });
        }
        console.log("volume", datiIniziali.volume);
        setVolume(datiIniziali.volume);

        console.log("Playlist caricata con successo:", datiIniziali.playlist);
      } catch (err) {
        console.error("Errore nel caricamento della playlist da Python:", err);
      }
    };

    avviaApp();

    // 2. POLLING WEBCAM: Ogni 33ms aggiorniamo il fotogramma sul tag img
    const timerWebcam = setInterval(async () => {
      if (window.pywebview && window.pywebview.api) {
        const frameBase64 = await window.pywebview.api.get_latest_frame();
        if (frameBase64 && videoRef.current) {
          videoRef.current.src = `data:image/jpeg;base64,${frameBase64}`;
        }
      }
    }, 33); // ~30 FPS

    // 3. POLLING COMANDI: Ogni 200ms controlliamo le gesture (Play / Pausa)
    const timerComandi = setInterval(async () => {
      if (window.pywebview && window.pywebview.api) {
        const comando = await window.pywebview.api.get_command();
        console.log("COMANDO ARRIVATO", comando);

        const currentList = playlistRef.current;
        const currentIndex = currentSongRef.current.index;
        if (comando.startsWith("VOL:")) {
          const volume = parseFloat(comando.split(":")[1]);
          volumeRef.current = volume;
          setVolume(volume);
        } else
          switch (comando) {
            case "PLAY":
              setIsPlaying(true);
              break;
            case "PAUSE":
              setIsPlaying(false);
              break;
            case "NEXT": {
              const nextIndex = currentIndex + 1;
              console.log("chiamato next");
              if (nextIndex < currentList.length) {
                console.log("aggiorno");
                const brano = currentList[nextIndex];
                const nuovoBrano = {
                  name: brano.name,
                  artist: brano.artist || "Local File",
                  albumArt: brano.albumArt || "",
                  dati: brano.dati || "",
                  index: nextIndex,
                };
                currentSongRef.current = nuovoBrano; // Aggiorniamo subito il ref
                setCurrentSong(nuovoBrano);
                setIsPlaying(true);
              } else {
                console.log("Fine della playlist raggiunta.");
              }
              break;
            }
            case "PREV": {
              const prevIndex = currentIndex - 1;
              const branoPrev = currentList[prevIndex];
              const branoPrecedenteOggetto = {
                name: branoPrev.name,
                artist: branoPrev.artist || "Local File",
                albumArt: branoPrev.albumArt || "",
                dati: branoPrev.dati || "",
                index: prevIndex,
              };
              currentSongRef.current = branoPrecedenteOggetto; // Aggiorniamo subito il ref
              setCurrentSong(branoPrecedenteOggetto);
              break;
            }
          }
      }
    }, 200);

    // Pulizia dei timer allo smontaggio del componente
    return () => {
      clearInterval(timerWebcam);
      clearInterval(timerComandi);
    };
  }, []);
  useEffect(() => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.play().catch((err) => {
        console.log(
          "Riproduzione audio bloccata o in attesa di interazione:",
          err,
        );
      });
    } else {
      audioRef.current.pause();
    }
  }, [isPlaying, currentSong]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = Math.max(0, Math.min(1, volume));
    }
  }, [volume]);
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-green-500 flex items-center justify-center">
      {/* 1. Il flusso video fa da sfondo a tutto */}
      <img
        id="video-stream"
        className="absolute inset-0 w-full h-full object-cover"
        ref={videoRef}
        alt="Webcam Stream"
      />
      <audio
        ref={audioRef}
        src={currentSong ? `data:audio/mp3;base64,${currentSong.dati}` : ""}
        onEnded={() => {
          console.log("Brano terminato");
        }}
      />
      <div className="bg-black/80 p-1 absolute top-10 right-10 h-48 w-6 flex flex-col rounded overflow-hidden border border-white/20 z-50">
        {/* Parte vuota / rimanente in alto */}
        <div
          style={{ height: `${100 - volume * 100}%` }}
          className="w-full transition-all duration-100"
        ></div>
        {/* Parte attiva del volume in basso */}
        <div
          style={{ height: `${volume * 100}%` }}
          className="bg-red-500 w-full transition-all duration-100"
        ></div>
      </div>
      {/* 2. La barra dei controlli fluttuante in basso */}
      <Player
        isPlaying={isPlaying}
        setIsPlaying={setIsPlaying}
        currentSong={currentSong}
      />
    </div>
  );
}

export default App;
