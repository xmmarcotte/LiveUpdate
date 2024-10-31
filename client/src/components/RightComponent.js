/* RightComponent.js */
import React, { useEffect, useState } from 'react';
import defaultCatImage from '../cat.jpg';
import defaultDogImage from '../dog.jpg';

const RightComponent = ({ showRight, setShowRight }) => {
    const [catContent, setCatContent] = useState({ image: null, fact: null });
    const [dogContent, setDogContent] = useState({ image: null, fact: null });

    const isVideo = (url) => {
        return url.match(/\.(mp4|webm)$/i) != null;
    };

    useEffect(() => {
        const fetchCatData = async () => {
            try {
                const imageResponse = await fetch('https://cataas.com/cat?json=true');
                const imageData = await imageResponse.json();
                const catMediaUrl = imageData.mimetype.includes('.mp4')
                    ? 'https://cataas.com/cat?' + imageData._id
                    : 'https://cataas.com/cat?' + imageData._id;

                setCatContent(prev => ({ ...prev, image: catMediaUrl }));
            } catch (error) {
                console.error("Error fetching cat data from cataas:", error);
                // Trying another API if the first one fails
                try {
                    const backupResponse = await fetch('https://api.thecatapi.com/v1/images/search');
                    const backupData = await backupResponse.json();
                    const backupImageUrl = backupData[0].url;

                    setCatContent(prev => ({ ...prev, image: backupImageUrl }));
                } catch (backupError) {
                    console.error("Error fetching cat data from the backup API:", backupError);
                    setCatContent({ image: defaultCatImage, fact: 'Could not fetch cat fact.' });
                }
            }

            try {
                const factResponse = await fetch('https://catfact.ninja/fact');
                const factData = await factResponse.json();
                setCatContent(prev => ({ ...prev, fact: factData.fact || 'No fact found' }));
            } catch (error) {
                console.error("Error fetching cat fact:", error);
                setCatContent(prev => ({ ...prev, fact: 'Could not fetch cat fact.' }));
            }
        };

        fetchCatData();
    }, []);

    useEffect(() => {
        const fetchDogData = async () => {
            try {
                const imageResponse = await fetch('https://random.dog/woof.json');
                const imageData = await imageResponse.json();
                const dogMediaUrl = isVideo(imageData.url) ? imageData.url : imageData.url;

                setDogContent(prev => ({ ...prev, image: dogMediaUrl }));
            } catch (error) {
                console.error("Error fetching dog image:", error);
                setDogContent({ image: defaultDogImage, fact: 'Could not fetch dog fact.' });
            }

            try {
                const factResponse = await fetch('https://dogapi.dog/api/v2/facts');
                const factData = await factResponse.json();
                const dogFactText = factData.data.length > 0 ? factData.data[0].attributes.body : 'No fact found';

                setDogContent(prev => ({ ...prev, fact: dogFactText }));
            } catch (error) {
                console.error("Error fetching dog fact:", error);
                setDogContent(prev => ({ ...prev, fact: 'Could not fetch dog fact.' }));
            }
        };

        fetchDogData();
    }, []);

    if (!catContent.image || !catContent.fact || !dogContent.image || !dogContent.fact) {
        return (
            <div className={`right-container ${showRight ? 'show' : ''}`}>
                <button
                    className={`right-toggle-button ${showRight ? 'show' : ''}`}
                    onClick={() => setShowRight(!showRight)}
                >
                    {showRight ? '>' : '<'}
                </button>
                <div className="right-frame">
                    <div className='right-message'>Loading...</div>
                </div>
            </div>
        );
    }

    return (
        <div className={`right-container ${showRight ? 'show' : ''}`}>
            <button
                className="right-toggle-button"
                onClick={() => setShowRight(!showRight)}
            >
                {showRight ? '>' : '<'}
            </button>
            <div className="right-frame">
                <div className='right-message'>
                    <div className='right-header'>Cat of the Day</div>
                    <div className='right-value'>
                        {isVideo(catContent.image) ? (
                            <video
                                src={catContent.image}
                                alt="Cat of the Day"
                                autoPlay
                                loop
                                muted
                            />
                        ) : (
                            <img src={catContent.image} alt="Cat of the Day" />
                        )}
                        <p>{catContent.fact}</p>
                    </div>
                </div>
                <div className='right-message'>
                    <div className='right-header'>Dog of the Day</div>
                    <div className='right-value'>
                        {isVideo(dogContent.image) ? (
                            <video
                                src={dogContent.image}
                                alt="Dog of the Day"
                                autoPlay
                                loop
                                muted
                            />
                        ) : (
                            <img src={dogContent.image} alt="Dog of the Day" />
                        )}
                        <p>{dogContent.fact}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RightComponent;
