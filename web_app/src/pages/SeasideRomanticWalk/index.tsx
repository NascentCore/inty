/**
 * SeasideRomanticWalk 页面
 * 展示「海边浪漫傍晚漫步」场景内容
 */
import { history } from '@umijs/max';
import React from 'react';
import './index.less';

const experienceHighlights: string[] = [
  'Warm sunset sky and slow ocean breeze.',
  'Guided prompts for intimate, relaxed conversation.',
  'A focused moment to reconnect without distractions.',
];

const suggestedMoments: string[] = [
  'Share one memory that still makes you smile.',
  'Describe the color of the sky right now in one sentence.',
  'Say one thing you appreciate about this moment together.',
];

const SeasideRomanticWalkPage: React.FC = () => {
  const handleBackToHome = (): void => {
    history.push('/');
  };

  const handleStartChat = (): void => {
    history.push('/');
  };

  return (
    <div className="seaside-romantic-walk-page">
      <section className="seaside-romantic-walk-page__hero">
        <div className="seaside-romantic-walk-page__hero-overlay" />
        <div className="seaside-romantic-walk-page__hero-content">
          <span className="seaside-romantic-walk-page__tag">SCENARIO EXPERIENCE</span>
          <h1 className="seaside-romantic-walk-page__title">Seaside Romantic Evening Walk</h1>
          <p className="seaside-romantic-walk-page__subtitle">
            A gentle sunset scene designed for calm emotions and meaningful connection.
          </p>
          <div className="seaside-romantic-walk-page__hero-actions">
            <button
              type="button"
              className="seaside-romantic-walk-page__primary-action"
              onClick={handleStartChat}
            >
              Start this mood
            </button>
            <button
              type="button"
              className="seaside-romantic-walk-page__secondary-action"
              onClick={handleBackToHome}
            >
              Back to home
            </button>
          </div>
        </div>
      </section>

      <section className="seaside-romantic-walk-page__content">
        <article className="seaside-romantic-walk-page__panel">
          <h2 className="seaside-romantic-walk-page__panel-title">Why this scene works</h2>
          <ul className="seaside-romantic-walk-page__list">
            {experienceHighlights.map((item) => (
              <li key={item} className="seaside-romantic-walk-page__list-item">
                {item}
              </li>
            ))}
          </ul>
        </article>

        <article className="seaside-romantic-walk-page__panel">
          <h2 className="seaside-romantic-walk-page__panel-title">Suggested conversation moments</h2>
          <ol className="seaside-romantic-walk-page__ordered-list">
            {suggestedMoments.map((item) => (
              <li key={item} className="seaside-romantic-walk-page__ordered-list-item">
                {item}
              </li>
            ))}
          </ol>
        </article>
      </section>
    </div>
  );
};

export default SeasideRomanticWalkPage;
