
const requiredEnv = [
    "NODE_RED_ADMIN_USER",
    "NODE_RED_ADMIN_PASSWORD_HASH",
    "NODE_RED_CREDENTIAL_SECRET"
];

for (const key of requiredEnv) {
    if (!process.env[key]) {
        throw new Error(`Missing required environment variable: ${key}`);
    }
}


module.exports = {
    // Server configuration
    uiPort: process.env.PORT || 1880,
    uiHost: "0.0.0.0",

    // Flow storage
    userDir: "/data",
    flowFile: "flows.json",
    flowFilePretty: true,

    // Encryption key for stored credentials
    credentialSecret: process.env.NODE_RED_CREDENTIAL_SECRET,

    // Editor authentication
    adminAuth: {
        type: "credentials",
        users: [
            {
                username: process.env.NODE_RED_ADMIN_USER,
                password: process.env.NODE_RED_ADMIN_PASSWORD_HASH,
                permissions: "*"
            }
        ]
    },

    // Runtime configuration
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    // Context storage
    contextStorage: {
        default: {
            module: "localfilesystem"
        }
    },

    // Function node settings
    functionGlobalContext: {},

    // Disable unnecessary external HTTP endpoints
    httpNodeRoot: "/api",

    // Editor configuration
    editorTheme: {
        projects: {
            enabled: false
        }
    }
};
