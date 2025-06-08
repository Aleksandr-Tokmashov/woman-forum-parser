// api/mlApi.ts
const API_URL = 'http://localhost:5000/api';

export const analyzeText = async (text: string): Promise<string | boolean> => {
  const response = await fetch(`${API_URL}/analyze_text`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  const data = await response.json();
  return data.negativity_detected ? data.constructive_response : false;
};