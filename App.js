import React, { useEffect, useRef } from 'react';
import { Buffer } from 'buffer';
import io from 'socket.io-client';

const App = () => {
  const videoRef = useRef(null);

  useEffect(() => {
    // Connect to the Socket.IO server
    const socket = io('http://192.168.188.29:5001'); // Ensure the backend is running at this address and port

    // Listen for the 'video_frame' event
    socket.on('video_frame', (data) => {
      if (videoRef.current) {
        window.Buffer = window.Buffer || Buffer;
        const imgData = `data:image/jpeg;base64,${Buffer.from(data.frame).toString('base64')}`;
        // const imgData = `data:image/jpeg;base64,${btoa(
        //   String.fromCharCode(...new Uint8Array(data.frame))
        // )}`;
        videoRef.current.src = imgData; // Update the image source
      }
    });

    // Clean up the socket connection on unmount
    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Live Video Feed</h1>
      <img
        ref={videoRef}
        alt="Video Feed"
        style={{ width: '640px', height: '480px', border: '1px solid black' }}
      />
    </div>
  );
};

export default App;
