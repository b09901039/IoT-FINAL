import React, { useEffect, useRef } from 'react';
import { Buffer } from 'buffer';
import io from 'socket.io-client';

const App = () => {
  const videoRef = useRef(null);

  useEffect(() => {
    const socket = io('http://192.168.188.29:5001'); // Ensure the backend is running at this address and port

    socket.on('video_frame', (data) => {
      if (videoRef.current) {
        window.Buffer = window.Buffer || Buffer;
        const imgData = `data:image/jpeg;base64,${Buffer.from(data.frame).toString('base64')}`;
        // const imgData = `data:image/jpeg;base64,${btoa(
        //   String.fromCharCode(...new Uint8Array(data.frame))
        // )}`;
        videoRef.current.src = imgData; 
      }
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Piano Assistant</h1>
      <img
        ref={videoRef}
        alt="Video Feed"
        style={{ width: '640px', height: '480px', border: '1px solid black' }}
      />
    </div>
  );
};

export default App;
