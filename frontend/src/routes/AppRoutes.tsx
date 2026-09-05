import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { HomePage } from '../pages/HomePage';
import { RecipeSearchPage } from '../pages/RecipeSearchPage';
import { RecipeDetailPage } from '../pages/RecipeDetailPage';
import { GroceryPage } from '../pages/GroceryPage';
import { CookingPage, CookingPageWithBoundary } from '../pages/CookingPage';
import { PantryPage } from '../pages/PantryPage';
import { ProfilePage } from '../pages/ProfilePage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/recipes" element={<RecipeSearchPage />} />
      <Route path="/recipes/:id" element={<RecipeDetailPage />} />
      <Route path="/grocery" element={<GroceryPage />} />
      <Route path="/cooking" element={<CookingPageWithBoundary />} />
      <Route path="/cooking/:sessionId" element={<CookingPageWithBoundary />} />
      <Route path="/pantry" element={<PantryPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
