
const axios = require('axios');

module.exports = async function (context, req) {
  const CLIENT_ID = process.env.TDX_CLIENT_ID;
  const CLIENT_SECRET = process.env.TDX_CLIENT_SECRET;
  const STOP_ID = "NWT163345";

  try {
    const tokenRes = await axios.post("https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token", new URLSearchParams({
      grant_type: "client_credentials",
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET
    }));

    const token = tokenRes.data.access_token;

    const [etaA, etaB] = await Promise.all([
      axios.get(`https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/NewTaipei/967?$filter=StopID eq '${STOP_ID}'&$format=JSON`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
      axios.get(`https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/NewTaipei/967直?$filter=StopID eq '${STOP_ID}'&$format=JSON`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
    ]);

    context.res = {
      headers: { "Content-Type": "application/json" },
      body: {
        routes: [
          { route: "967", eta: etaA.data },
          { route: "967直", eta: etaB.data }
        ]
      }
    };
  } catch (err) {
    context.res = {
      status: 500,
      body: { error: err.message }
    };
  }
};
