using CosmosEmbeddingGenerator;
using Microsoft.Azure.Cosmos;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;


var builder = FunctionsApplication.CreateBuilder(args);
builder.Configuration.AddJsonFile("appsettings.json", optional: true, reloadOnChange: true);

builder.Services.Configure<CosmosEmbeddingOptions>(builder.Configuration.GetSection("CosmosEmbeddingOptions"));
builder.ConfigureFunctionsWebApplication();
builder.ConfigureCosmosDBExtensionOptions(options =>
{
    options.ClientOptions.ConsistencyLevel = ConsistencyLevel.Eventual;
});


var host = builder.Build();

host.Run();