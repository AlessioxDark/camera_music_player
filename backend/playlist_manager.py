import os
def get_playlist():
    file_audio_salvati = []
    
    for nome_file in  os.listdir("./playlist"):
        percorso_completo = os.path.join("./playlist", nome_file)
        
        # Controlla che sia un file e non una cartella
        if os.path.isfile(percorso_completo):
            # Apriamo il file, leggiamo tutti i suoi byte e lo chiudiamo subito
            with open(percorso_completo, 'rb') as f:
                dati_file = f.read() 
                file_audio_salvati.append({    "nome": os.path.splitext(nome_file)[0],"dati":dati_file})
    
    return file_audio_salvati   # Configura le tue credenziali e lo scope necessario


isPlaying = False
currentSong = 0
file_playlist = get_playlist()
volume = 0.5
def skipSong():
    global currentSong
    if currentSong+1 <= len(get_playlist())-1:
        currentSong+=1

    
def prevSong():
    global currentSong
    if currentSong-1 >=0:
        currentSong-=1
    




