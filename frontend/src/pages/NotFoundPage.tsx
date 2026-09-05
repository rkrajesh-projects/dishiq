import React from 'react';
import { Link } from 'react-router-dom';
import { Home, Compass } from 'lucide-react';
import { PageContainer } from '../components/common/PageContainer';
import { Button } from '../components/common/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <PageContainer className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="p-4 bg-orange-50 text-orange-600 rounded-full mb-4">
        <Compass className="w-12 h-12" />
      </div>
      <h1 className="text-4xl font-extrabold text-gray-900 mb-2">404</h1>
      <h2 className="text-xl font-bold text-gray-800 mb-2">Recipe or Page Not Found</h2>
      <p className="text-sm text-gray-600 max-w-sm mb-6">
        The kitchen page you are looking for doesn't exist or has been moved.
      </p>
      <Link to="/">
        <Button variant="primary" icon={<Home className="w-4 h-4" />}>
          Back to Home
        </Button>
      </Link>
    </PageContainer>
  );
};
