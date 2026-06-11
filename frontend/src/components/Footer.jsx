import React from 'react';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-surface-container-high border-t border-border-glass py-8">
      <div className="max-w-container-max mx-auto px-margin-desktop">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div>
            <h3 className="font-headline-md text-on-surface mb-4">Persona Hub</h3>
            <p className="text-on-surface-variant text-sm">
              The world's most comprehensive AI persona marketplace.
            </p>
          </div>
          <div>
            <h4 className="font-label-caps text-on-surface-variant mb-4 uppercase">Product</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="/catalog" className="text-on-surface-variant hover:text-on-surface">Catalog</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Pricing</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Features</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-label-caps text-on-surface-variant mb-4 uppercase">Company</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">About</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Blog</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Contact</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-label-caps text-on-surface-variant mb-4 uppercase">Legal</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Privacy</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Terms</a></li>
              <li><a href="#" className="text-on-surface-variant hover:text-on-surface">Security</a></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border-glass pt-8">
          <p className="text-center text-on-surface-variant text-sm">
            © {currentYear} Persona Hub. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
