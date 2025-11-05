import React from 'react';
import './index.less';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-links">
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          <a href="https://umijs.org" target="_blank" rel="noopener noreferrer">
            UmiJS
          </a>
          <a href="https://react.dev" target="_blank" rel="noopener noreferrer">
            React
          </a>
        </div>
        <div className="footer-copyright">Copyright © {currentYear} My Chat App</div>
      </div>
    </footer>
  );
};

export default Footer;
